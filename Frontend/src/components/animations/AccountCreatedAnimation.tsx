import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, Sparkles, User, Mail, Shield } from 'lucide-react';

interface AccountCreatedAnimationProps {
  isVisible: boolean;
  userEmail: string;
  userName: string;
  onComplete: () => void;
}

export const AccountCreatedAnimation: React.FC<AccountCreatedAnimationProps> = ({
  isVisible,
  userEmail,
  userName,
  onComplete
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  
  const steps = [
    { icon: CheckCircle, title: "Email Verified", color: "text-green-400" },
    { icon: User, title: "Profile Created", color: "text-blue-400" },
    { icon: Shield, title: "Account Secured", color: "text-purple-400" },
    { icon: Sparkles, title: "Welcome to PRISM AI!", color: "text-yellow-400" }
  ];

  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(() => {
        if (currentStep < steps.length - 1) {
          setCurrentStep(prev => prev + 1);
        } else {
          // Complete animation after showing final step
          setTimeout(() => {
            onComplete();
            setCurrentStep(0); // Reset for next time
          }, 2000);
        }
      }, 800);
      
      return () => clearTimeout(timer);
    }
  }, [isVisible, currentStep, onComplete, steps.length]);

  const containerVariants = {
    hidden: { opacity: 0, scale: 0.8 },
    visible: { 
      opacity: 1, 
      scale: 1,
      transition: { 
        duration: 0.5,
        ease: "easeOut"
      }
    },
    exit: { 
      opacity: 0, 
      scale: 0.8,
      transition: { 
        duration: 0.3 
      }
    }
  };

  const stepVariants = {
    hidden: { opacity: 0, x: 50, scale: 0.8 },
    visible: { 
      opacity: 1, 
      x: 0, 
      scale: 1,
      transition: { 
        duration: 0.6,
        ease: "easeOut"
      }
    },
    exit: { 
      opacity: 0, 
      x: -50, 
      scale: 0.8,
      transition: { 
        duration: 0.3 
      }
    }
  };

  const sparkleVariants = {
    animate: {
      rotate: [0, 360],
      scale: [1, 1.2, 1],
      transition: {
        duration: 2,
        repeat: Infinity,
        ease: "easeInOut"
      }
    }
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-3xl p-12 max-w-md w-full mx-4 border border-slate-700/50 shadow-2xl"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            {/* Animated Background Pattern */}
            <div className="absolute inset-0 rounded-3xl overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-cyan-500/10 animate-pulse"></div>
              <motion.div
                className="absolute -inset-10 bg-gradient-to-r from-purple-500/5 via-blue-500/5 to-cyan-500/5"
                animate={{
                  rotate: [0, 360],
                  scale: [1, 1.1, 1]
                }}
                transition={{
                  duration: 10,
                  repeat: Infinity,
                  ease: "linear"
                }}
              />
            </div>

            {/* Content */}
            <div className="relative z-10 text-center">
              {/* Main Icon */}
              <motion.div
                className="flex justify-center mb-8"
                animate={currentStep === steps.length - 1 ? sparkleVariants.animate : {}}
              >
                {React.createElement(steps[Math.min(currentStep, steps.length - 1)].icon, {
                  className: `w-20 h-20 ${steps[Math.min(currentStep, steps.length - 1)].color}`,
                  strokeWidth: 1.5
                })}
              </motion.div>

              {/* Progress Steps */}
              <div className="flex justify-center space-x-2 mb-8">
                {steps.map((step, index) => (
                  <motion.div
                    key={index}
                    className={`w-3 h-3 rounded-full transition-all duration-500 ${
                      index <= currentStep 
                        ? 'bg-gradient-to-r from-purple-500 to-blue-500' 
                        : 'bg-slate-600'
                    }`}
                    initial={{ scale: 0.8 }}
                    animate={{ 
                      scale: index === currentStep ? 1.2 : 1,
                      opacity: index <= currentStep ? 1 : 0.5
                    }}
                    transition={{ duration: 0.3 }}
                  />
                ))}
              </div>

              {/* Animated Step Content */}
              <AnimatePresence mode="wait">
                <motion.div
                  key={currentStep}
                  variants={stepVariants}
                  initial="hidden"
                  animate="visible"
                  exit="exit"
                  className="min-h-[120px] flex flex-col justify-center"
                >
                  <h2 className="text-2xl font-bold text-white mb-3">
                    {steps[currentStep].title}
                  </h2>
                  
                  {currentStep === 0 && (
                    <p className="text-slate-300 text-sm">
                      ✅ {userEmail} verified successfully
                    </p>
                  )}
                  
                  {currentStep === 1 && (
                    <div className="space-y-2">
                      <p className="text-slate-300 text-sm">
                        👋 Hello, {userName}!
                      </p>
                      <p className="text-slate-400 text-xs">
                        Your profile has been created
                      </p>
                    </div>
                  )}
                  
                  {currentStep === 2 && (
                    <p className="text-slate-300 text-sm">
                      🔒 Your account is now secure and protected
                    </p>
                  )}
                  
                  {currentStep === 3 && (
                    <div className="space-y-3">
                      <p className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-blue-400 to-cyan-400 font-medium">
                        🎉 Account created successfully!
                      </p>
                      <p className="text-slate-400 text-xs">
                        Get ready to explore the power of AI
                      </p>
                    </div>
                  )}
                </motion.div>
              </AnimatePresence>

              {/* Animated Loading Bar */}
              <div className="mt-8">
                <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-purple-500 via-blue-500 to-cyan-500 rounded-full"
                    initial={{ width: "0%" }}
                    animate={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                  />
                </div>
                <p className="text-slate-400 text-xs mt-3">
                  {currentStep < steps.length - 1 
                    ? "Setting up your account..." 
                    : "Welcome aboard! 🚀"
                  }
                </p>
              </div>
            </div>

            {/* Floating Particles */}
            {currentStep === steps.length - 1 && (
              <>
                {[...Array(8)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="absolute w-2 h-2 bg-gradient-to-r from-purple-400 to-blue-400 rounded-full"
                    initial={{ 
                      opacity: 0,
                      x: "50%",
                      y: "50%"
                    }}
                    animate={{
                      opacity: [0, 1, 0],
                      x: `${50 + (Math.cos(i * 45 * Math.PI / 180) * 100)}%`,
                      y: `${50 + (Math.sin(i * 45 * Math.PI / 180) * 100)}%`,
                      scale: [0, 1, 0]
                    }}
                    transition={{
                      duration: 2,
                      delay: i * 0.1,
                      repeat: Infinity,
                      ease: "easeInOut"
                    }}
                  />
                ))}
              </>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default AccountCreatedAnimation;